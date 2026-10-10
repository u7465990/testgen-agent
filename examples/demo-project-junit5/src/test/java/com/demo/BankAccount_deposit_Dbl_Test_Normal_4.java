package com.demo;

import com.demo.BankAccount;
import java.lang.reflect.Field;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

public class BankAccount_deposit_Dbl_Test_Normal_4 {


    @Test
    public void testDepositWithRepresentativeValues() throws Exception {
        BankAccount account = new BankAccount("Alice", 100.0);

        Field balanceField = BankAccount.class.getDeclaredField("balance");
        balanceField.setAccessible(true);

        account.deposit(1.0);
        assertEquals(101.0, (double) balanceField.get(account), 0.0001);

        assertThrows(IllegalArgumentException.class, () -> account.deposit(0.0));
        assertEquals(101.0, (double) balanceField.get(account), 0.0001);

        assertThrows(IllegalArgumentException.class, () -> account.deposit(-1.0));
        assertEquals(101.0, (double) balanceField.get(account), 0.0001);
    }

}
