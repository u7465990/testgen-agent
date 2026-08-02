package com.demo;

import com.demo.BankAccount;
import java.lang.reflect.Field;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_withdraw_Dbl_Test_Normal_6 {


    @Test
    public void withdraw_NormalTest() throws Exception {
        BankAccount account = new BankAccount("Alice", 10.0);

        account.withdraw(1.0);

        Field balanceField = account.getClass().getDeclaredField("balance");
        balanceField.setAccessible(true);
        double actualBalance = balanceField.getDouble(account);

        Assert.assertEquals(9.0, actualBalance, 0.0001);
    }

}
