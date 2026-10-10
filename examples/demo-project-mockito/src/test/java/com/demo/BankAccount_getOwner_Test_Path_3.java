package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_getOwner_Test_Path_3 {


    @Test
    public void testGetOwner() {
        BankAccount account = new BankAccount("Alice", 100.0);
        String owner = account.getOwner();
        Assert.assertEquals("Alice", owner);
    }

}
