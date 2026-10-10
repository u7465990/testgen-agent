package com.demo;

import com.demo.BankAccount;
import java.lang.reflect.Field;
import org.junit.Test;
import org.junit.Assert;

public class BankAccount_deposit_Dbl_Test_Normal_4 {


    @Test
    public void testDepositWithValidAmount() throws Exception {
        BankAccount account = new BankAccount("Alice", 100.0);

        account.deposit(1.0);

        Field balanceField = BankAccount.class.getDeclaredField("balance");
        balanceField.setAccessible(true);
        double balance = balanceField.getDouble(account);

        Assert.assertEquals(101.0, balance, 0.0001);
    }

}
